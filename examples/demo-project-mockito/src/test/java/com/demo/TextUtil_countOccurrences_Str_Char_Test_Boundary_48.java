package com.demo;

import com.demo.TextUtil;
import org.junit.Test;
import org.junit.Assert;

public class TextUtil_countOccurrences_Str_Char_Test_Boundary_48 {


    @Test
    public void testCountOccurrencesWithNullString() {
        char c = 'a';
        int result = TextUtil.countOccurrences(null, c);
        Assert.assertEquals(0, result);
    }

}
