- extract the top level website - https://cse.umn.edu and convert it into a markdown file - done
- recursively do the same for all the embedded links
    - extract all the links in the top level mark down file - done
    - find a better way to name each of the md files for each of the links (warning: some of the url have dashes) - done
        - first see some example of links you're dealing with - done
        - process the links (what kind of links to remove searching deeper?) - done
    - have a global list of links extracted. (should it be in a list or recorded in a file? --> a json file)
        - make sure the all the links in the global list are unique - done
        - when extracting the links, check against the global list to see if the link has been extracted before - done

    - load the json files
    - input a list of urls to be extracted - done
    - extract the extracted_embedded_links too
    - try using the many_arun()
    - sort the queue of links to be extracted based on relevance - done

    - apply locks on the json files

            